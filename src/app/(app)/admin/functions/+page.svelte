<script>
	import { onMount } from 'svelte';
	import { functions } from '$shared/stores';

	import { getFunctions } from '$api/functions';
	import Functions from '$features/admin/Functions.svelte';

	onMount(async () => {
		await Promise.all([
			(async () => {
				functions.set(await getFunctions(localStorage.token));
			})()
		]);
	});
</script>

{#if $functions !== null}
	<Functions />
{/if}
